<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { http } from '@/api/client'

interface Course { name: string; teacher?: string; location?: string; weekday: number; period_start: number; period_end: number; weeks_raw?: string; weeks?: number[]; source?: string }
interface WeeklyResponse { ok?: boolean; week?: number; courses?: Course[]; error?: string; message?: string }
const days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
const periods = Array.from({ length: 11 }, (_, i) => i + 1)
const currentWeek = ref(isoWeek(new Date()))
const courses = ref<Course[]>([])
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const editor = ref<{ weekday: number; start: number; end: number; name: string; location: string } | null>(null)

function isoWeek(date: Date) {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()))
  const day = d.getUTCDay() || 7
  d.setUTCDate(d.getUTCDate() + 4 - day)
  const start = new Date(Date.UTC(d.getUTCFullYear(), 0, 1))
  return Math.ceil((((d.getTime() - start.getTime()) / 86400000) + 1) / 7)
}
function dayNumber(index: number) {
  const now = new Date()
  const monday = new Date(now); monday.setHours(0, 0, 0, 0)
  monday.setDate(monday.getDate() - ((monday.getDay() + 6) % 7) + index)
  return `${monday.getMonth() + 1}/${monday.getDate()}`
}
const weekLabel = computed(() => `第 ${currentWeek.value} 周`)
const courseAt = (day: number, period: number) => courses.value.filter(c => c.weekday === day && c.period_start === period).sort((a, b) => a.period_end - b.period_end)
const dayCourseCount = (day: number) => courses.value.filter(c => c.weekday === day).length
async function load() {
  loading.value = true; error.value = ''
  try {
    const result = await http.get<WeeklyResponse>('/api/weekly-plan?week=' + currentWeek.value)
    if (result.ok === false) throw new Error(result.message || result.error || '读取失败')
    courses.value = Array.isArray(result.courses) ? result.courses : []
  } catch (e) { error.value = e instanceof Error ? e.message : '读取失败'; courses.value = [] } finally { loading.value = false }
}
function shiftWeek(delta: number) { currentWeek.value = Math.max(1, currentWeek.value + delta); void load() }
function openEditor(day: number, period: number) { editor.value = { weekday: day, start: period, end: period, name: '', location: '' }; error.value = '' }
async function saveEditor() {
  if (!editor.value || saving.value) return
  const name = editor.value.name.trim()
  if (!name) { error.value = '请填写课程名'; return }
  const start = Math.min(editor.value.start, editor.value.end)
  const end = Math.max(editor.value.start, editor.value.end)
  const next = [...courses.value, { name, location: editor.value.location.trim(), teacher: '', weekday: editor.value.weekday, period_start: start, period_end: end, source: 'manual' }]
  await persist(next)
  if (!error.value) editor.value = null
}
async function removeCourse(course: Course) {
  await persist(courses.value.filter(item => item !== course))
}
async function persist(next: Course[]) {
  saving.value = true; error.value = ''
  const previous = courses.value
  courses.value = next
  try {
    const result = await http.post<WeeklyResponse>('/api/weekly-plan', { week: currentWeek.value, courses: next })
    if (result.ok === false) throw new Error(result.message || result.error || '保存失败')
    await load()
  } catch (e) { courses.value = previous; error.value = e instanceof Error ? e.message : '保存失败' } finally { saving.value = false }
}
onMounted(load)
</script>

<template>
  <section class="weekly">
    <header class="head">
      <div><h1>周计划表</h1><p>{{ weekLabel }} · {{ courses.length }} 个节次 · 按周配置节次与时间</p></div>
      <div class="week-nav"><button type="button" @click="shiftWeek(-1)">‹</button><b>{{ weekLabel }}</b><button type="button" @click="shiftWeek(1)">›</button></div>
      <button class="refresh" type="button" :disabled="loading" @click="load">{{ loading ? '读取中…' : '刷新' }}</button>
    </header>
    <div v-if="error" class="notice error">{{ error }}</div>
    <div class="legend"><span>点击空格子添加节次</span><span>节次会保存到当前 ISO 周</span></div>
    <div class="week-grid">
      <div class="corner"></div>
      <div v-for="(day, index) in days" :key="day" class="dayhead"><b>{{ day }}</b><small>{{ dayNumber(index) }} · {{ dayCourseCount(index + 1) }} 节</small></div>
      <template v-for="period in periods" :key="period">
        <div class="period"><b>第 {{ period }} 节</b><small>{{ period <= 4 ? '上午' : period <= 8 ? '下午' : '晚上' }}</small></div>
        <div v-for="(day, index) in days" :key="day + period" class="cell" :class="{ filled: courseAt(index + 1, period).length }" @click="!courseAt(index + 1, period).length && openEditor(index + 1, period)">
          <div v-for="course in courseAt(index + 1, period)" :key="course.name + course.period_start" class="course">
            <b>{{ course.name }}</b>
            <small>{{ course.period_start === course.period_end ? `第 ${course.period_start} 节` : `第 ${course.period_start}–${course.period_end} 节` }}<template v-if="course.location"> · {{ course.location }}</template></small>
            <button type="button" :disabled="saving" @click.stop="removeCourse(course)">×</button>
          </div>
        </div>
      </template>
    </div>
    <div v-if="editor" class="editor">
      <div class="editor-head"><b>{{ days[editor.weekday - 1] }} · 第 {{ editor.start }} 节</b><button type="button" @click="editor = null">×</button></div>
      <input v-model="editor.name" placeholder="课程名，例如：高等数学" autofocus>
      <input v-model="editor.location" placeholder="地点（可选）">
      <div class="range"><label>开始<input v-model.number="editor.start" type="number" min="1" max="11"></label><label>结束<input v-model.number="editor.end" type="number" min="1" max="11"></label><button type="button" :disabled="saving" @click="saveEditor">{{ saving ? '保存中…' : '添加节次' }}</button></div>
    </div>
    <div v-if="loading && !courses.length" class="empty">正在读取周计划…</div>
    <div v-else-if="!loading && !courses.length" class="empty">这一周还没有节次，点击格子添加</div>
  </section>
</template>

<style scoped>
.weekly{flex:1;min-height:0;overflow:auto;padding:22px 24px 26px;background:#f7faff;color:#17263b;box-sizing:border-box;width:100%}.head{display:flex;align-items:flex-end;gap:9px;margin-bottom:10px;flex-wrap:wrap}.head h1{margin:0;font-size:24px;letter-spacing:-.03em}.head p{margin:3px 0 0;font-size:10px;color:#8a9bb0}.week-nav{display:flex;align-items:center;gap:5px;margin-left:auto}.week-nav button{width:25px;height:25px;border:1px solid #dbe8ff;border-radius:6px;background:#fff;color:#2563eb;font:13px inherit;cursor:pointer}.week-nav b{font-size:9.5px;color:#314a65;min-width:52px;text-align:center}.refresh{height:29px;border:1px solid #dbe8ff;border-radius:8px;background:#fff;color:#2563eb;font:9px inherit;padding:0 9px;cursor:pointer}.notice.error{border:1px solid #fecaca;background:#fff5f5;color:#b91c1c;border-radius:8px;padding:7px 9px;font-size:9px;margin-bottom:8px}.legend{display:flex;justify-content:space-between;font-size:8px;color:#9aabc0;margin-bottom:7px}
.week-grid{display:grid;grid-template-columns:62px repeat(7,minmax(0,1fr));border:1px solid #e3ebf7;border-radius:11px;overflow:hidden;background:#fff}.corner{background:#f8fbff;border-bottom:1px solid #e3ebf7}.dayhead{background:#f8fbff;border-bottom:1px solid #e3ebf7;border-left:1px solid #f1f5fb;padding:7px 6px;text-align:center}.dayhead b{display:block;font-size:9px;color:#405872}.dayhead small{display:block;font-size:7px;color:#9aabc0;margin-top:2px}.period{border-bottom:1px solid #f1f5fb;background:#fbfdff;padding:7px 6px}.period b{display:block;font-size:8px;color:#526982}.period small{display:block;font-size:6.5px;color:#a2b2c6;margin-top:2px}.cell{min-height:48px;border-bottom:1px solid #f1f5fb;border-left:1px solid #f1f5fb;padding:3px;cursor:pointer;transition:background .16s}.cell:hover{background:#f8fbff}.cell.filled{cursor:default}.course{height:100%;min-height:42px;border-left:2px solid #2563eb;border-radius:5px;background:#eef4ff;padding:5px 6px;position:relative}.course b{display:block;font-size:8px;color:#1e3a5f;line-height:1.45;padding-right:9px}.course small{display:block;font-size:6.5px;color:#7d90a7;margin-top:2px;line-height:1.4}.course button{position:absolute;right:2px;top:1px;border:0;background:none;color:#9aabc0;font:12px inherit;cursor:pointer;padding:0}.course button:hover{color:#b23b52}
.editor{border:1px solid #dbe8ff;border-radius:10px;background:#fff;padding:10px;margin-top:9px;max-width:620px}.editor-head{display:flex;align-items:center;margin-bottom:7px}.editor-head b{font-size:10px;color:#314a65}.editor-head button{margin-left:auto;border:0;background:none;color:#8a9bb0;font-size:15px;cursor:pointer}.editor input{display:block;width:100%;height:29px;border:1px solid #dbe8ff;border-radius:7px;background:#f8fbff;padding:0 8px;font:10px inherit;outline:0;box-sizing:border-box;margin-bottom:6px}.range{display:flex;align-items:flex-end;gap:6px}.range label{font-size:8px;color:#8a9bb0}.range input{width:58px;margin-top:3px}.range button{height:29px;border:0;border-radius:7px;background:#2563eb;color:#fff;font:9px inherit;padding:0 11px;cursor:pointer;margin-left:auto}.empty{border:1px dashed #cfe0f7;border-radius:10px;background:#fff;padding:18px;text-align:center;color:#9aabc0;font-size:9px;margin-top:9px}
@media(max-width:1180px){.weekly{padding:18px 18px 22px}.week-grid{grid-template-columns:54px repeat(7,minmax(0,1fr))}.course b{font-size:7.5px}}
</style>
