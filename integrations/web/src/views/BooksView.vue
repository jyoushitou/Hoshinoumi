<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { http } from '@/api/client'

interface Progress { chapter?: number; percent?: number; updated_at?: string }
interface Book { id: string; title: string; author?: string; format: string; size?: number; progress?: Progress | null }
const router = useRouter()
const books = ref<Book[]>([])
const loading = ref(false)
const error = ref('')
const refreshing = ref(false)
const root = ref('data/books')
const continueBook = computed(() => books.value.find(book => book.progress) || books.value[0] || null)
function percent(book: Book) { return Math.max(0, Math.min(100, Math.round(Number(book.progress?.percent || 0)))) }
function sizeLabel(size?: number) { const n = Number(size || 0); return n > 1024 * 1024 ? (n / 1024 / 1024).toFixed(1) + ' MB' : Math.max(1, Math.round(n / 1024)) + ' KB' }
function open(book: Book) { void router.push('/books/' + encodeURIComponent(book.id)) }
async function load() {
  loading.value = true; error.value = ''
  try {
    const result = await http.get<{ data?: Book[]; root?: string }>('/api/books')
    books.value = Array.isArray(result.data) ? result.data : []
    root.value = result.root || 'data/books'
  } catch (e) { error.value = e instanceof Error ? e.message : '书架读取失败' } finally { loading.value = false }
}
async function refresh() {
  refreshing.value = true
  try { await http.post('/api/books/refresh', {}); await load() } catch (e) { error.value = e instanceof Error ? e.message : '刷新失败' } finally { refreshing.value = false }
}
onMounted(load)
</script>

<template>
  <section class="books">
    <header class="head"><div><h1>阅读</h1><p>本地书架 · TXT / EPUB</p></div><button class="refresh" type="button" :disabled="refreshing" @click="refresh">{{ refreshing ? '扫描中…' : '重新扫描' }}</button></header>
    <div v-if="error" class="notice">{{ error }}</div>
    <div v-if="continueBook" class="continue" @click="open(continueBook)">
      <small>继续阅读</small><b>{{ continueBook.title }}</b><span>{{ continueBook.progress ? '第 ' + (Number(continueBook.progress.chapter || 0) + 1) + ' 章 · ' + percent(continueBook) + '%' : '尚未开始' }}</span><em>继续 ›</em>
    </div>
    <div v-if="loading" class="empty">正在扫描书架…</div>
    <div v-else-if="!books.length" class="empty"><b>书架为空</b><span>把 .txt / .epub 放进 <code>{{ root }}</code>，再点重新扫描。</span></div>
    <div v-else class="grid">
      <article v-for="book in books" :key="book.id" class="card" @click="open(book)">
        <div class="cover" :class="book.format"><span>{{ (book.title || '书').slice(0, 1) }}</span><small>{{ book.format.toUpperCase() }}</small></div>
        <div class="meta"><b>{{ book.title }}</b><span>{{ book.author || '未署名' }} · {{ sizeLabel(book.size) }}</span><div class="bar"><i :style="{ width: percent(book) + '%' }" /></div><small>{{ book.progress ? percent(book) + '% · 第 ' + (Number(book.progress.chapter || 0) + 1) + ' 章' : '未开始' }}</small></div>
      </article>
    </div>
  </section>
</template>

<style scoped>
.books{flex:1;min-height:0;overflow:auto;padding:22px 24px 28px;background:#f7faff;color:#17263b;box-sizing:border-box;width:100%}.head{display:flex;align-items:flex-end;gap:10px;margin-bottom:12px}.head h1{margin:0;font-size:24px;letter-spacing:-.03em}.head p{margin:3px 0 0;font-size:10px;color:#8a9bb0}.refresh{margin-left:auto;height:29px;border:1px solid #dbe8ff;border-radius:8px;background:#fff;color:#2563eb;font:9px inherit;padding:0 10px;cursor:pointer}.notice{border:1px solid #fecaca;background:#fff5f5;color:#b91c1c;border-radius:8px;padding:7px 9px;font-size:9px;margin-bottom:9px}
.continue{display:flex;align-items:center;gap:9px;background:linear-gradient(135deg,#eff6ff,#fff);border:1px solid #dbe8ff;border-radius:11px;padding:11px 12px;margin-bottom:11px;cursor:pointer}.continue small{font-size:7px;color:#7d8ca3;letter-spacing:.08em}.continue b{font-size:12px;color:#1e3a5f;margin-left:4px}.continue span{font-size:8px;color:#8a9bb0}.continue em{margin-left:auto;font-style:normal;color:#2563eb;font-size:9px}
.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px}.card{display:flex;gap:10px;background:#fff;border:1px solid #e3ebf7;border-radius:11px;padding:10px;cursor:pointer;transition:border-color .18s,transform .18s}.card:hover{border-color:#bcd4f7;transform:translateY(-1px)}.cover{width:62px;height:82px;border-radius:7px;background:linear-gradient(135deg,#dbeafe,#93c5fd);display:flex;flex-direction:column;align-items:center;justify-content:center;color:#1e3a5f;flex:none;box-shadow:0 5px 12px rgba(37,99,235,.15)}.cover.epub{background:linear-gradient(135deg,#ede9fe,#c4b5fd)}.cover span{font-size:22px;font-weight:800}.cover small{font-size:6px;margin-top:4px;letter-spacing:.08em}.meta{min-width:0;display:flex;flex-direction:column}.meta b{font-size:11px;color:#1e3a5f;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.meta>span{font-size:8px;color:#8a9bb0;margin-top:3px}.bar{height:4px;border-radius:4px;background:#eef3fa;margin:9px 0 4px;overflow:hidden}.bar i{display:block;height:100%;background:#2563eb;border-radius:4px}.meta>small{font-size:7.5px;color:#9aabc0}
.empty{border:1px dashed #cfe0f7;border-radius:11px;background:#fff;padding:28px;text-align:center;color:#9aabc0;font-size:9px;line-height:1.8}.empty b{display:block;color:#526982;font-size:11px;margin-bottom:3px}.empty code{font-family:ui-monospace,monospace;color:#2563eb}
@media(max-width:1180px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:820px){.books{padding:16px 14px 20px}.grid{grid-template-columns:1fr}.head h1{font-size:22px}.continue{flex-wrap:wrap}.continue em{margin-left:0}}
</style>
