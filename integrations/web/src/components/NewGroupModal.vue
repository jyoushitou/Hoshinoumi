<script setup lang="ts">
import { ref } from 'vue'
import { http } from '@/api/client'
defineProps<{ open: boolean }>()
const emit = defineEmits<{ (e: 'close'): void; (e: 'created', id: string): void }>()
const name = ref('')
const members = ref('')
const busy = ref(false)
const error = ref('')
async function create() {
  if (!name.value.trim()) { error.value = '群名不能为空'; return }
  busy.value = true
  error.value = ''
  try {
    const list = members.value.split(/[,，\s]+/).map(x => x.trim()).filter(Boolean)
    const r = await http.post<{ id?: string; message?: string }>('/api/groups', { name: name.value.trim(), members: list })
    if (!r.id) throw new Error(r.message || '创建失败')
    name.value = ''
    members.value = ''
    emit('created', r.id)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '创建失败'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div v-if="open" class="mask" @click.self="emit('close')">
    <div class="card">
      <header><b>新建群聊</b><button type="button" @click="emit('close')">×</button></header>
      <label>群名<input v-model="name" maxlength="40" placeholder="例如：周末出游"></label>
      <label>成员 QQ<textarea v-model="members" rows="2" placeholder="逗号或空格分隔，可留空"></textarea></label>
      <div v-if="error" class="error">{{ error }}</div>
      <button class="primary" type="button" :disabled="busy" @click="create">{{ busy ? '创建中…' : '创建群聊' }}</button>
    </div>
  </div>
</template>

<style scoped>
.mask{position:fixed;inset:0;z-index:60;background:rgba(15,23,42,.35);backdrop-filter:blur(3px);display:flex;align-items:center;justify-content:center;padding:18px}.card{width:100%;max-width:360px;background:#fff;border:1px solid #dbe8ff;border-radius:14px;padding:15px;box-shadow:0 18px 45px rgba(37,99,235,.18)}header{display:flex;align-items:center;margin-bottom:10px}header b{font-size:14px;color:#17263b}header button{margin-left:auto;border:0;background:none;color:#8a9bb0;font-size:18px;cursor:pointer}label{display:block;font-size:9px;color:#8a9bb0;margin-bottom:9px}input,textarea{display:block;width:100%;box-sizing:border-box;border:1px solid #dbe8ff;border-radius:8px;background:#f8fbff;color:#243b55;font:10.5px inherit;outline:0;padding:7px 8px;margin-top:3px;resize:vertical}input:focus,textarea:focus{border-color:#93b7fa;box-shadow:0 0 0 3px rgba(37,99,235,.08)}.primary{width:100%;height:32px;border:0;border-radius:8px;background:#2563eb;color:#fff;font:10px inherit;font-weight:700;cursor:pointer}.primary:disabled{opacity:.55}.error{font-size:9px;color:#b91c1c;background:#fff5f5;border:1px solid #fecaca;border-radius:6px;padding:5px 7px;margin-bottom:7px}
</style>
