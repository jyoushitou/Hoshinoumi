<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useMobileNav } from '@/composables/useMobileNav'
import { useAuthStore } from '@/stores/auth'
import { useIsOwner } from '@/composables/useIsOwner'

const router = useRouter()
const auth = useAuthStore()
const isOwner = useIsOwner()
const { entries, quickKeys, toggleQuick, resetQuick } = useMobileNav()
const visibleEntries = computed(() => isOwner.value ? entries : entries.filter(entry => entry.key !== 'relation'))
const message = computed(() => `${quickKeys.value.length} / 5`)
const quickLabel = computed(() => quickKeys.value.map(key => entries.find(entry => entry.key === key)?.label).filter(Boolean).join(' / '))

function toggle(key: string) { toggleQuick(key) }
function logout() { auth.logout() }
function openPermissions() { void router.push('/settings/permissions') }
function changeBackend() {
  const bridge = (window as any).HoshinoumiConfig
  if (bridge?.open) bridge.open()
  else window.alert('请在 Hoshinoumi App 内修改后端地址')
}
</script>

<template>
  <section class="mobile-settings">
    <div class="head"><h1>设置</h1><p>连接 / 快捷栏 / 账号</p></div>

    <div class="block">
      <div class="block-title">底部快捷栏 <span>{{ message }}</span></div>
      <p class="block-desc">1–5 个图标入口，收起时显示在底部。当前：{{ quickLabel }}</p>
      <div class="quick-grid">
        <button
          v-for="entry in visibleEntries"
          :key="entry.key"
          type="button"
          class="quick-item"
          :class="{ on: quickKeys.includes(entry.key) }"
          @click="toggle(entry.key)"
        >
          <b>{{ entry.icon }}</b><span>{{ entry.label }}</span><em v-if="quickKeys.includes(entry.key)">✓</em>
        </button>
      </div>
      <button class="reset" type="button" @click="resetQuick">恢复默认</button>
    </div>

    <div class="block">
      <div class="row"><span>后端连接</span><small>{{ auth.loggedIn ? '已登录' : '未登录' }}</small></div>
      <button class="row backend-row" type="button" @click="changeBackend"><span>后端地址</span><small>修改 ›</small></button>
      <button class="row backend-row" type="button" @click="openPermissions"><span>权限与后台</span><small>管理 ›</small></button>
      <div class="row"><span>账号</span><small>{{ auth.qq || '—' }}</small></div>
      <div class="row"><span>版本</span><small>v35.7</small></div>
    </div>

    <button class="logout" type="button" @click="logout">退出登录</button>
    <div class="about-card"><b>关于 Hoshinoumi</b><span>v35.7 · Mobile Web</span><div class="about-links"><a href="https://github.com/jyoushitou/Hoshinoumi" target="_blank" rel="noopener">GitHub</a><a href="https://github.com/jyoushitou" target="_blank" rel="noopener">作者 jyoushitou</a></div><em>POWERED BY JYOUSHITOU</em></div>
  </section>
</template>

<style scoped>
.mobile-settings{padding:16px 14px 18px;background:#f7faff;min-height:100%}
.head h1{margin:0;font-size:24px;letter-spacing:-.03em;line-height:1.15}.head p{margin:4px 0 14px;color:#8a9bb0;font-size:10px}
.block{background:#fff;border:1px solid #e3ebf7;border-radius:13px;padding:12px;margin-bottom:10px}
.block-title{display:flex;justify-content:space-between;font-size:11px;font-weight:750;color:#314a65}.block-title span{font-size:9px;color:#8a9bb0;font-weight:400}
.block-desc{font-size:8.5px;color:#8a9bb0;line-height:1.6;margin:4px 0 9px}
.quick-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:6px}
.quick-item{position:relative;height:45px;border:1px solid #e1ebf9;background:#f8fbff;border-radius:8px;color:#607896;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;font-size:8px;cursor:pointer}
.quick-item b{font-size:14px;font-weight:400;line-height:1}.quick-item em{position:absolute;right:4px;top:2px;font-style:normal;color:#2563eb;font-size:8px}
.quick-item.on{border-color:#93c5fd;background:#eef4ff;color:#2563eb;font-weight:700}
.reset{width:100%;margin-top:8px;height:30px;border:1px solid #dbe8ff;background:#fff;color:#2563eb;border-radius:8px;font:10px inherit;cursor:pointer}
.row{display:flex;justify-content:space-between;align-items:center;padding:9px 0;border-bottom:1px solid #f0f5fd;font-size:10px;color:#3d5470}.row:last-child{border-bottom:0}.row small{font-size:9px;color:#9aabc0}.backend-row{width:100%;border:0;background:none;text-align:left;cursor:pointer}.backend-row small{color:#2563eb}
.about-card{margin-top:12px;padding:13px;border:1px solid #e3ebf7;border-radius:13px;background:#fff;text-align:center}.about-card b{display:block;font-size:10px;color:#314a65}.about-card span{display:block;font-size:8px;color:#9aabc0;margin-top:3px}.about-card em{display:block;font:7px ui-monospace,monospace;letter-spacing:.12em;color:#a8b5c7;font-style:normal;margin-top:7px}.about-links{display:flex;justify-content:center;gap:6px;flex-wrap:wrap;margin-top:8px}.about-links a{font-size:8px;text-decoration:none;border-radius:6px;padding:2px 7px;color:#2563eb;border:1px solid #dbe8ff;background:#f4f9ff}.about-links a:last-child{color:#607795;border-color:#e3ebf7;background:#fff}
.logout{width:100%;height:36px;border:1px solid #fecaca;background:#fff5f5;color:#b91c1c;border-radius:9px;font:10px inherit;cursor:pointer}
</style>
