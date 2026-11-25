<script setup lang="ts">
import { ref } from 'vue'
import { ApiError, http } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { useSessionStore } from '@/stores/session'
const auth = useAuthStore(); const session = useSessionStore()
const qq = ref(auth.qq); const token = ref(''); const password = ref(''); const setupCode = ref(''); const status = ref(auth.authError || ''); const saving = ref(false); const mode = ref<'login' | 'setup' | 'token'>('login')
async function loginReal(qqValue: string, passwordValue: string, setupCodeValue = '') {
  const result = await http.post<{ ok?: boolean; token?: string; tokens?: { access?: string }; message?: string }>('/api/login', {
    user_id: qqValue, password: passwordValue, setup_code: setupCodeValue,
  })
  const token = result.tokens?.access || result.token
  if (!token) throw new Error(result.message || '登录失败')
  return token
}

function errorCode(e: unknown) {
  return e instanceof ApiError ? String((e.data as { error?: string } | undefined)?.error || '') : ''
}

async function setupReal(qqValue: string, passwordValue: string, code: string) {
  try {
    return await loginReal(qqValue, passwordValue, code)
  } catch (e) {
    if (errorCode(e) === 'password_setup_required') throw new Error('setup code 不正确或已过期，请让 owner 重新添加')
    if (errorCode(e) === 'invalid_credentials' && code) {
      await http.post('/api/register', { user_id: qqValue, invite: code, password: passwordValue, nickname: qqValue })
      return await loginReal(qqValue, passwordValue, code)
    }
    throw e
  }
}

async function save() {
  if (!qq.value.trim()) { status.value = '请填写 QQ'; return }
  saving.value = true; status.value = '正在连接…'
  try {
    let nextToken = token.value.trim()
    if (mode.value === 'token') {
      if (!nextToken) throw new Error('token 不能为空')
    } else if (mode.value === 'login') {
      nextToken = await loginReal(qq.value.trim(), password.value)
    } else {
      if (password.value.length < 8) throw new Error('密码至少 8 位')
      nextToken = await setupReal(qq.value.trim(), password.value, setupCode.value.trim())
    }
    http.setToken(nextToken)
    await http.get('/healthz')
    await http.get('/api/status')
    auth.setCredentials(nextToken, qq.value.trim())
    await session.refresh()
    status.value = '已连接'
  } catch (e) {
    if (errorCode(e) === 'password_setup_required') {
      mode.value = 'setup'
      status.value = '该 QQ 还没有密码，请输入 owner 添加时生成的 setup code，并设置新密码'
      return
    }
    if (errorCode(e) === 'password_too_short') { status.value = '密码至少 8 位'; return }
    status.value = '连接失败：' + (e instanceof Error ? e.message : String(e))
  }
  finally { saving.value = false }
}
</script>
<template>
  <div class="mask">
    <div class="card">
      <h2>连接 Hoshinoumi</h2>
      <p class="sub">owner 添加 QQ 后会生成 setup code；首次用 setup code 设置密码。<br>已有密码直接登录，后端地址使用当前站点。</p>
      <div class="modes">
        <button type="button" :class="{ on: mode === 'login' }" @click="mode = 'login'">密码登录</button>
        <button type="button" :class="{ on: mode === 'setup' }" @click="mode = 'setup'">首次设置</button>
        <button type="button" :class="{ on: mode === 'token' }" @click="mode = 'token'">Token</button>
      </div>
      <label>QQ<input v-model="qq" placeholder="请输入 QQ"></label>
      <label v-if="mode === 'token'">访问 token<input v-model="token" type="password" placeholder="Bearer token"></label>
      <template v-else>
        <label>密码<input v-model="password" type="password" placeholder="密码（首次登录即设置，至少 8 位）"></label>
        <label v-if="mode === 'setup'">setup code<input v-model="setupCode" placeholder="owner 添加 QQ 时生成"></label>
      </template>
      <div class="actions"><button class="primary" :disabled="saving" @click="save">{{ saving ? '连接中…' : '保存并进入' }}</button></div>
      <div class="status">{{ status }}</div>
    </div>
  </div>
</template>
<style scoped>
.mask{position:fixed;inset:0;z-index:50;background:rgba(15,23,42,.35);backdrop-filter:blur(3px);display:flex;align-items:center;justify-content:center;padding:20px 16px;overflow:auto}.card{width:100%;max-width:420px;background:#fff;border:1px solid #dbe8ff;border-radius:14px;padding:18px;box-shadow:0 18px 45px rgba(37,99,235,.16)}.modes{display:flex;gap:5px;margin:0 0 10px}.modes button{flex:1;border:1px solid #dbe8ff;border-radius:6px;background:#f8fbff;color:#6b7c95;font:9px inherit;padding:4px 3px;cursor:pointer}.modes button.on{background:#eef4ff;color:#2563eb;border-color:#93b7fa;font-weight:700}h2{margin:0 0 5px;font-size:15px;color:#17263b}.sub{font-size:10px;color:#6b7c95;line-height:1.6;margin-bottom:13px}label{display:block;font-size:9px;color:#8a9bb0;margin-bottom:9px}input{display:block;width:100%;border:1px solid #dbe8ff;border-radius:7px;background:#f8fbff;color:#243b55;font:10.5px inherit;outline:0;padding:7px 8px;margin-top:3px}input:focus{border-color:#93b7fa;box-shadow:0 0 0 3px rgba(37,99,235,.08)}.actions{display:flex;gap:6px;margin-top:4px}.actions button{width:100%;border:1px solid #dbe8ff;border-radius:7px;background:#fff;color:#2563eb;font-size:10px;padding:7px;cursor:pointer}.actions button.primary{background:#2563eb;border-color:#2563eb;color:#fff}.status{font-size:9px;color:#8a9bb0;margin-top:8px;min-height:14px}
@media (max-width:820px){.mask{align-items:center;padding:calc(56px + env(safe-area-inset-top)) 16px calc(20px + env(safe-area-inset-bottom))}.card{margin:auto 0;transform:translateY(-10px)}}
</style>
