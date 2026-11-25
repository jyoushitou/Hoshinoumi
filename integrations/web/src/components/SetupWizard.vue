<script setup lang="ts">
import { ref } from 'vue'
import { http } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { useSessionStore } from '@/stores/session'

defineProps<{ open: boolean }>()
const emit = defineEmits<{ (e: 'close'): void; (e: 'done'): void }>()
const auth = useAuthStore()
const session = useSessionStore()
const nickname = ref('')
const busy = ref(false)
const error = ref('')

async function finish() {
  busy.value = true
  error.value = ''
  try {
    await http.post('/api/setup', { nickname: nickname.value.trim() })
    await session.refresh()
    emit('done')
  } catch (e) {
    error.value = e instanceof Error ? e.message : '初始化失败'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div v-if="open" class="setup-mask">
    <div class="setup-card">
      <div class="badge">FIRST RUN · OWNER</div>
      <h2>初始化主人空间</h2>
      <p class="lead">这是第一次打开主人界面。确认基础数据后开始使用。</p>

      <label class="field">
        <span>主人昵称</span>
        <input v-model="nickname" maxlength="40" placeholder="例如：主人">
      </label>

      <div class="defaults">
        <div class="defaults-title">将初始化</div>
        <div class="default-row"><b>存钱账户</b><span>银行卡 / 微信 / 支付宝 / 现金</span></div>
        <div class="default-row"><b>主人身份</b><span>{{ auth.qq || '—' }}</span></div>
        <div class="default-row"><b>对话记忆</b><span>首次聊天后自动写入</span></div>
      </div>

      <div v-if="error" class="error">{{ error }}</div>
      <div class="actions">
        <button type="button" class="later" @click="emit('close')">稍后</button>
        <button type="button" class="primary" :disabled="busy" @click="finish">{{ busy ? '初始化中…' : '完成初始化' }}</button>
      </div>
      <p class="hint">只初始化默认账户和主人空间，不写入虚假流水。</p>
    </div>
  </div>
</template>

<style scoped>
.setup-mask{position:fixed;inset:0;z-index:80;background:rgba(15,23,42,.3);backdrop-filter:blur(5px);display:flex;align-items:center;justify-content:center;padding:18px}
.setup-card{width:100%;max-width:430px;background:#fff;border:1px solid #dbe8ff;border-radius:18px;padding:22px;box-shadow:0 24px 70px rgba(15,23,42,.22)}
.badge{display:inline-block;font-size:8px;letter-spacing:.14em;color:#2563eb;background:#eef4ff;border:1px solid #dbe8ff;border-radius:20px;padding:4px 8px}
h2{margin:10px 0 4px;font-size:21px;letter-spacing:-.03em;color:#17263b}
.lead{margin:0 0 16px;font-size:10px;line-height:1.6;color:#8a9bb0}
.field{display:block;margin-bottom:14px}.field span{display:block;font-size:9px;color:#6b7c95;margin-bottom:5px}.field input{width:100%;box-sizing:border-box;height:36px;border:1px solid #dbe8ff;border-radius:9px;background:#f8fbff;color:#243b55;font:11px inherit;padding:0 10px;outline:0}.field input:focus{border-color:#93b7fa;box-shadow:0 0 0 3px rgba(37,99,235,.08)}
.defaults{border:1px solid #e3ebf7;border-radius:11px;background:#f8fbff;padding:10px 11px;margin-bottom:13px}.defaults-title{font-size:8px;letter-spacing:.12em;color:#8a9bb0;margin-bottom:5px}.default-row{display:flex;justify-content:space-between;gap:10px;font-size:9px;color:#8a9bb0;padding:4px 0;border-bottom:1px solid #eef3fb}.default-row:last-child{border-bottom:0}.default-row b{font-weight:600;color:#405872}.default-row span{text-align:right}
.error{font-size:9px;color:#b91c1c;background:#fff5f5;border:1px solid #fecaca;border-radius:7px;padding:6px 8px;margin-bottom:9px}
.actions{display:flex;gap:8px;justify-content:flex-end}.actions button{height:33px;border-radius:8px;font:10px inherit;padding:0 14px;cursor:pointer}.later{border:1px solid #e3ebf7;background:#fff;color:#7d8ca3}.primary{border:0;background:#2563eb;color:#fff;font-weight:700}.primary:disabled{opacity:.55}.hint{margin:10px 0 0;font-size:8px;color:#9aabbe;text-align:right}
</style>
