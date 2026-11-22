<script setup lang="ts">
import { ref } from 'vue'
import { http } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { useSessionStore } from '@/stores/session'
const auth = useAuthStore(); const session = useSessionStore()
const qq = ref(auth.qq); const token = ref(''); const status = ref(auth.authError || ''); const saving = ref(false)
async function save() {
  if (!qq.value.trim() || !token.value.trim()) { status.value = 'QQ 和 token 都要填'; return }
  saving.value = true; status.value = '正在连接…'
  http.setToken(token.value.trim())
  try {
    await http.get('/healthz')
    await http.get('/api/status')
    auth.setCredentials(token.value, qq.value)
    await session.refresh()
    status.value = '已连接'
  } catch (e) { status.value = '连接失败：' + (e instanceof Error ? e.message : String(e)) }
  finally { saving.value = false }
}
function skip() { auth.enterGuest() }
</script>
<template>
  <div class="mask">
    <div class="card">
      <h2>连接 Hoshinoumi</h2>
      <p class="sub">第一次使用，填写主人 QQ 和访问 token。<br>后端地址使用当前站点，不需要填写 URL。</p>
      <label>主人 QQ<input v-model="qq" placeholder="请输入主人 QQ"></label>
      <label>访问 token<input v-model="token" type="password" placeholder="Bearer token"></label>
      <div class="actions"><button class="primary" :disabled="saving" @click="save">{{ saving ? '连接中…' : '保存并进入' }}</button><button @click="skip">稍后配置</button></div>
      <div class="status">{{ status }}</div>
    </div>
  </div>
</template>
<style scoped>
.mask{position:fixed;inset:0;z-index:50;background:rgba(15,23,42,.35);backdrop-filter:blur(3px);display:flex;align-items:flex-start;justify-content:center;padding:80px 16px;overflow:auto}.card{width:100%;max-width:420px;background:#fff;border:1px solid #dbe8ff;border-radius:14px;padding:18px;box-shadow:0 18px 45px rgba(37,99,235,.16)}h2{margin:0 0 5px;font-size:15px;color:#17263b}.sub{font-size:10px;color:#6b7c95;line-height:1.6;margin-bottom:13px}label{display:block;font-size:9px;color:#8a9bb0;margin-bottom:9px}input{display:block;width:100%;border:1px solid #dbe8ff;border-radius:7px;background:#f8fbff;color:#243b55;font:10.5px inherit;outline:0;padding:7px 8px;margin-top:3px}input:focus{border-color:#93b7fa;box-shadow:0 0 0 3px rgba(37,99,235,.08)}.actions{display:flex;gap:6px;margin-top:4px}.actions button{flex:1;border:1px solid #dbe8ff;border-radius:7px;background:#fff;color:#2563eb;font-size:10px;padding:7px;cursor:pointer}.actions button.primary{background:#2563eb;border-color:#2563eb;color:#fff}.status{font-size:9px;color:#8a9bb0;margin-top:8px;min-height:14px}
</style>
