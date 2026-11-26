<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { http } from '@/api/client'

interface Toc { index: number; title: string }
interface BookDetail { id: string; title: string; author?: string; format: string; chapters?: Toc[]; chapter_count?: number }
interface Chapter { chapter: number; title: string; content: string; chapter_count: number; prev?: number | null; next?: number | null }
const route = useRoute()
const router = useRouter()
const book = ref<BookDetail | null>(null)
const chapter = ref<Chapter | null>(null)
const loading = ref(false)
const error = ref('')
const tocOpen = ref(false)
const fontSize = ref(Number(localStorage.getItem('hoshinoumi.reader.font') || 17))
const lineHeight = ref(Number(localStorage.getItem('hoshinoumi.reader.line') || 1.9))
const theme = ref<'light' | 'paper' | 'dark'>(localStorage.getItem('hoshinoumi.reader.theme') as 'light' | 'paper' | 'dark' || 'light')
const contentEl = ref<HTMLElement | null>(null)
const current = computed(() => Number(chapter.value?.chapter || 0))
const total = computed(() => Number(chapter.value?.chapter_count || book.value?.chapter_count || 0))
const progress = computed(() => total.value ? Math.round(((current.value + 1) / total.value) * 100) : 0)
const toc = computed(() => book.value?.chapters || [])
watch(fontSize, v => localStorage.setItem('hoshinoumi.reader.font', String(v)))
watch(lineHeight, v => localStorage.setItem('hoshinoumi.reader.line', String(v)))
watch(theme, v => localStorage.setItem('hoshinoumi.reader.theme', v))

async function loadBook() {
  loading.value = true; error.value = ''
  try {
    const id = String(route.params.id || '')
    const detail = await http.get<{ data?: BookDetail; progress?: { chapter?: number } }>('/api/books/' + encodeURIComponent(id))
    book.value = detail.data || null
    const start = Number(detail.progress?.chapter || 0)
    await loadChapter(start)
  } catch (e) { error.value = e instanceof Error ? e.message : '打开失败' } finally { loading.value = false }
}
async function loadChapter(index: number) {
  if (!book.value) return
  try {
    const id = String(route.params.id || '')
    const result = await http.get<{ data?: Chapter }>('/api/books/' + encodeURIComponent(id) + '/content?chapter=' + Math.max(0, index))
    chapter.value = result.data || null
    tocOpen.value = false
    const percent = total.value ? Math.round(((current.value + 1) / total.value) * 100) : 0
    void http.put('/api/books/' + encodeURIComponent(id) + '/progress', { chapter: current.value, percent }).catch(() => {})
    await new Promise(resolve => setTimeout(resolve))
    contentEl.value?.scrollTo({ top: 0 })
    window.scrollTo({ top: 0 })
  } catch (e) { error.value = e instanceof Error ? e.message : '章节读取失败' }
}
function go(index?: number | null) { if (index === null || index === undefined) return; void loadChapter(index) }
function back() { void router.push('/books') }
onMounted(loadBook)
</script>

<template>
  <section class="reader" :class="theme">
    <header class="reader-head">
      <button type="button" class="icon" @click="back" aria-label="返回书架">‹</button>
      <div class="who"><b>{{ book?.title || '阅读器' }}</b><small>{{ book?.format?.toUpperCase() }} · {{ current + 1 }} / {{ total || '—' }}</small></div>
      <button type="button" class="icon" @click="tocOpen = !tocOpen" aria-label="目录">☰</button>
    </header>
    <div class="progress"><i :style="{ width: progress + '%' }" /><span>{{ progress }}%</span></div>
    <div v-if="error" class="notice">{{ error }}</div>
    <div v-if="loading" class="empty">正在打开…</div>
    <main v-else-if="chapter" ref="contentEl" class="content" :style="{ fontSize: fontSize + 'px', lineHeight: lineHeight }">
      <h1>{{ chapter.title }}</h1>
      <pre>{{ chapter.content }}</pre>
      <div class="chapter-actions"><button type="button" :disabled="chapter.prev == null" @click="go(chapter.prev)">‹ 上一章</button><button type="button" :disabled="chapter.next == null" @click="go(chapter.next)">下一章 ›</button></div>
    </main>
    <aside v-if="tocOpen" class="toc">
      <header><b>目录</b><button type="button" @click="tocOpen = false">×</button></header>
      <button v-for="item in toc" :key="item.index" type="button" :class="{ on: item.index === current }" @click="go(item.index)">{{ item.title }}</button>
    </aside>
    <div class="settings">
      <button type="button" @click="fontSize = Math.max(13, fontSize - 1)">A−</button>
      <span>{{ fontSize }}</span>
      <button type="button" @click="fontSize = Math.min(28, fontSize + 1)">A+</button>
      <button type="button" @click="lineHeight = lineHeight >= 2.2 ? 1.6 : Math.round((lineHeight + 0.15) * 100) / 100">行距</button>
      <button type="button" @click="theme = theme === 'light' ? 'paper' : theme === 'paper' ? 'dark' : 'light'">{{ theme === 'light' ? '纸张' : theme === 'paper' ? '夜间' : '日间' }}</button>
    </div>
  </section>
</template>

<style scoped>
.reader{position:relative;flex:1;min-height:0;overflow:hidden;display:flex;flex-direction:column;background:#f7faff;color:#17263b;box-sizing:border-box;width:100%}.reader.paper{background:#fbf6ea;color:#3d3326}.reader.dark{background:#111827;color:#dbe5f4}.reader-head{height:54px;flex:none;display:flex;align-items:center;gap:8px;padding:0 12px;border-bottom:1px solid #e3ebf7;background:#fff}.reader.dark .reader-head{background:#0f172a;border-color:#243247}.icon{width:32px;height:32px;border:1px solid #dbe8ff;border-radius:8px;background:#fff;color:#2563eb;font:16px inherit;cursor:pointer}.reader.dark .icon{background:#172033;border-color:#2b3b55;color:#93c5fd}.who{min-width:0;flex:1;text-align:center}.who b{display:block;font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.who small{display:block;font-size:7px;color:#9aabc0;margin-top:2px}.progress{height:3px;flex:none;background:#e8effa;position:relative}.progress i{display:block;height:100%;background:#2563eb}.progress span{position:absolute;right:8px;top:5px;font-size:7px;color:#9aabc0}
.content{flex:1;min-height:0;overflow:auto;padding:28px min(8vw,80px) 90px;max-width:900px;width:100%;margin:0 auto;box-sizing:border-box}.content h1{font-size:1.35em;margin:0 0 18px;letter-spacing:-.02em}.content pre{white-space:pre-wrap;word-break:break-word;font-family:inherit;margin:0;line-height:inherit}.chapter-actions{display:flex;gap:9px;justify-content:space-between;margin-top:30px}.chapter-actions button{flex:1;height:34px;border:1px solid #dbe8ff;border-radius:8px;background:#fff;color:#2563eb;font:9px inherit;cursor:pointer}.chapter-actions button:disabled{opacity:.4}.reader.dark .chapter-actions button,.reader.dark .toc button{background:#172033;border-color:#2b3b55;color:#bfdbfe}
.toc{position:absolute;z-index:30;right:10px;top:54px;bottom:50px;width:min(320px,78vw);background:#fff;border:1px solid #dbe8ff;border-radius:10px;box-shadow:0 16px 40px rgba(15,35,70,.2);overflow:auto;padding:8px}.reader.dark .toc{background:#0f172a;border-color:#243247}.toc header{display:flex;align-items:center;padding:3px 3px 8px;border-bottom:1px solid #eef3fb}.toc header b{font-size:10px}.toc header button{margin-left:auto;border:0;background:none;color:#8a9bb0;font:15px inherit;cursor:pointer}.toc>button{display:block;width:100%;text-align:left;border:0;background:none;color:#405872;font:9px inherit;padding:7px 6px;border-radius:6px;cursor:pointer;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.toc>button:hover,.toc>button.on{background:#eef4ff;color:#2563eb}
.settings{flex:none;height:44px;display:flex;align-items:center;gap:5px;padding:0 12px;border-top:1px solid #e3ebf7;background:#fff}.reader.dark .settings{background:#0f172a;border-color:#243247}.settings button{height:26px;border:1px solid #dbe8ff;border-radius:6px;background:#f8fbff;color:#526982;font:8px inherit;padding:0 7px;cursor:pointer}.settings span{font-size:8px;color:#9aabc0;min-width:16px;text-align:center}.reader.dark .settings button{background:#172033;border-color:#2b3b55;color:#cbd5e1}
.notice{margin:10px 16px;border:1px solid #fecaca;background:#fff5f5;color:#b91c1c;border-radius:8px;padding:7px 9px;font-size:9px}.empty{padding:30px;text-align:center;color:#9aabc0;font-size:10px}
@media(max-width:820px){.reader-head{padding-top:env(safe-area-inset-top);height:calc(50px + env(safe-area-inset-top))}.content{padding:20px 18px 90px}.toc{top:calc(50px + env(safe-area-inset-top));right:8px;bottom:58px}.settings{padding-bottom:env(safe-area-inset-bottom);height:calc(44px + env(safe-area-inset-bottom))}}
</style>
